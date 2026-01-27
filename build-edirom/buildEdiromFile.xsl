<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:edirom="http://www.edirom.de/ns/1.3" xmlns="http://www.edirom.de/ns/1.3" xmlns:xi="http://www.w3.org/2001/XInclude" xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs" version="3.0">

  <xsl:output indent="yes"/>
  <xsl:param name="properties-file" select="document('../../properties.xml')"/>
  <xsl:param name="editionHandle" select="$properties-file//property[@name = 'editionHandle']/text()"/>
  <xsl:param name="uuids" select="$properties-file//uuid"/>
  <xsl:param name="nav" select="document('./tmp/nav.xml')"/>
  <xsl:param name="concorances" select="document('./tmp/conc.xml')"/>

  <xsl:template match="edirom:edition">
    <edition xml:id="{$uuids[@name='edition']/text()}" xmlns="http://www.edirom.de/ns/1.3">
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()"/>
    </edition>
  </xsl:template>
  
  <xsl:template match="edirom:editionName">
    <editionName>
      <xsl:value-of select="$properties-file//property[@name = 'editionTitle']/text()" />
    </editionName>
  </xsl:template>

  <xsl:template match="edirom:work">
    <work xml:id="{$uuids[@name='editionWork']/text()}"
      xlink:href="{concat('xmldb:exist:///db/apps/edirom-content/', $editionHandle, '/structure/edirom-works.xml')}">
      <xsl:apply-templates select="@*[not(name() = ('xml:id', 'xlink:href'))] | node()" />
    </work>
  </xsl:template>

  <xsl:template match="edirom:preferences">
    <preferences
      xlink:href="{concat('xmldb:exist:///db/apps/edirom-content/', $editionHandle, '/prefs.xml')}"
    />
  </xsl:template>

  <xsl:template match="edirom:navigatorDefinition">
    <xsl:copy-of select="$nav"/>
  </xsl:template>

  <xsl:template match="edirom:concordances">
    <concordances xmlns="http://www.edirom.de/ns/1.3">
      <xsl:copy-of select="$concorances"/>
    </concordances>
  </xsl:template>

  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
