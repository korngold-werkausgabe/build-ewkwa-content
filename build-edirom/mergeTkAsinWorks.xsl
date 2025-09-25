<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:mei="http://www.music-encoding.org/ns/mei" xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs" version="2.0">
  
  <xsl:output indent="yes"/>
  
  <xsl:param name="annots" select="document('./tmp/annots.xml')"/>
  <xsl:param name="properties" select="document('../../properties.xml')" />
  <xsl:param name="uuids" select="$properties//uuid" />
  
  <xsl:template match="*">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="mei:mei">
    <mei:mei xml:id="{$uuids[@name='editionWork']/text()}">
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()" />
    </mei:mei>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:titleStmt/mei:title">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$properties//property[@name='workTitle']"/>
    </xsl:copy>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:editionStmt/mei:edition">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$properties//property[@name='editionTitle']"/>
    </xsl:copy>
  </xsl:template>
  
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work">
    <work xml:id="{$uuids[@name='work']/text()}">
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()" />
    </work>
  </xsl:template>
  
  <xsl:template match="//mei:work/mei:notesStmt/*">
    <xsl:copy-of select="$annots"/>
  </xsl:template>
    
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()" />
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>